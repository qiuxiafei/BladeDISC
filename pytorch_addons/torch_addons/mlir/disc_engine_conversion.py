import os
import subprocess
import shutil
import tempfile
from datetime import datetime

import torch
import torch_addons
from torch_addons.config import Config
from torch_addons import mlir
from torch_addons import tools
from torch_addons.clustering import support_fusion_group, support_group_conversion
from torch_addons.logging import logger

def _dump_to_tempfile(tmp_dir, dump_bytes):
    inp_file = tempfile.NamedTemporaryFile(dir=tmp_dir, delete=False)
    inp_file.write(bytes(dump_bytes, "utf-8"))
    inp_file.close()
    return inp_file

def _compile_torchscript(graph):
    # NB: Some MLIR debug information would be dump to mlir_dump_dir,
    # since the feature is not stable currently.
    # (Only files of the last run are reserved except for compile log.)
    mlir_dump_dir = "dump_dir"
    pkg_path = os.path.dirname(os.path.abspath(torch_addons.__file__))
    mhlo_bytes, pretty_bytes, input_dev_str, output_dev_str = mlir.cvt_torchscript_to_mhlo(graph)
    mhlo_compile_cmd = os.path.join(pkg_path, "disc_compiler_main")
    with tempfile.TemporaryDirectory() as tmp_dir:
        time_str = datetime.now().strftime('%Y_%m_%d-%H_%M_%S.%f')
        # dump the parsable/compilable mlir bytes into file
        inp_mlir_file = _dump_to_tempfile(tmp_dir, mhlo_bytes)
        # dump the pretty mlir bytes(for debug) into file
        mlir_pretty_file = _dump_to_tempfile(tmp_dir, pretty_bytes)
        if os.environ.get('TORCH_ADDONS_DEBUG_LOG', None) is None:
            mlir_dump_dir = os.path.join(tmp_dir, mlir_dump_dir)

        # copy mlir files to mlir_dump_dir
        if not os.path.exists(mlir_dump_dir):
            os.makedirs(mlir_dump_dir)
        assert os.path.isdir(mlir_dump_dir), "the dump mlir path must be a directory"
        with open(os.path.join(mlir_dump_dir, f'graph.{time_str}.txt'), 'w') as f:
            f.write(str(graph))
        # the mhlo_compiler output binary file
        out_file_name = tempfile.NamedTemporaryFile(
            dir=tmp_dir, suffix=".so", delete=False
        ).name

        # the mhlo_compiler output metadata file
        out_file_pbtxt = out_file_name + ".pbtxt"
        compile_log = os.devnull
        env = os.environ.copy()
        if os.environ.get("TORCH_ADDONS_DEBUG_LOG", None) is not None:
            compile_log = os.path.join(mlir_dump_dir, "mhlo_compile." + time_str + ".log")

        with open(compile_log, "w") as devnull:
            cfg = Config.get_current_context_or_new()
            env['TAO_MLIR_ENABLE_AMP'] = str(cfg.enable_mlir_amp).lower()
            # RUN: disc_compiler_main input_mlir_file.mlir output_file.so
            # redirect stdout to devnull
            subprocess.check_call(
                [mhlo_compile_cmd, inp_mlir_file.name, out_file_name, "--multi-cc-support"],
                stdout=devnull,
                stderr=devnull,
                env=env,
            )

        assert os.path.exists(out_file_name)
        assert os.path.exists(out_file_pbtxt)
        with open(out_file_name, "rb") as f:
            so_bytes = f.read()
        with open(out_file_pbtxt, "rb") as f_pbtxt:
            pb_bytes = f_pbtxt.read()

        if os.environ.get('TORCH_ADDONS_DEBUG_LOG', None) is not None: 
            # copy result to mlir_dump_dir
            shutil.move(out_file_name, os.path.join(mlir_dump_dir, f"out.{time_str}.so"))
            shutil.move(out_file_pbtxt, os.path.join(mlir_dump_dir, f"out.{time_str}.so.pbtxt"))
            shutil.move(inp_mlir_file.name, os.path.join(mlir_dump_dir, f"dump.{time_str}.mlir"))
            shutil.move(
                mlir_pretty_file.name, os.path.join(mlir_dump_dir, f"dump.{time_str}.pretty.mlir")
            )

        return so_bytes, pb_bytes, input_dev_str, output_dev_str

def _get_mlir_unsupported(graph):
    cfg = Config.get_current_context_or_new()
    extra_unspt_nodes = [n for n in graph.nodes() if n.kind() in cfg.customize_op_black_list]
    unspt_nodes = [n for n in graph.nodes() if not mlir.is_mlir_mhlo_supported(n)]
    return unspt_nodes + extra_unspt_nodes

def _disc_engine_conversion(module):
    def try_cvt_to_disc_engine_func(c_module, subgraph, group_name, q_info=None):
        attr_name = f"{mlir._DISC_GROUP_NAME}{group_name}"
        try:
            so_bytes, pb_bytes, input_dev_str, output_dev_str = _compile_torchscript(subgraph)
            subg_str = str(subgraph)
            inputs = subgraph.input_list()
            outputs = subgraph.output_list()
            otype = mlir.register_disc_engine(
                c_module, attr_name, so_bytes, pb_bytes, subg_str, inputs, outputs, input_dev_str, output_dev_str
            )
            return attr_name, otype
        except Exception as error:
            logger.warning(error)
            return None

    support_group_conversion.group_to_engine_conversion(
        module, try_cvt_to_disc_engine_func, adapt_number_ios=True
    )


def _optimize_mlir(script_module):
    """
    Given a ScriptModule, do MLIR optimization on it.

    Args:
        script_module(torch.jit.ScriptModule): PyTorch ScriptModule to be optimized by MLIR.
    """
    assert isinstance(
        script_module, torch.jit.ScriptModule
    ), "Only torch.jit.ScriptModule can be optimized by TensorRT, but {} is given.".format(
        type(script_module)
    )
    # do tensorrt optimization
    c_module = script_module._c
    graph = c_module.forward.graph

    # NOTE: this is NOT SAFE, since it assumes that the LHS is not aliased by
    # another value. This is only to avoid breaking ONNX export; when alias
    # analysis is done we can emit a warning if someone tries to export.
    #
    # TODO: Replace it with a safe version, that only replace inplace with out-of-place ops,
    # only when it's safe. Otherwise label the inplace ops as unsupported.
    # Then move the pass as a common step to _optimize_common.
    torch._C._jit_pass_remove_inplace_ops(graph)

    def fusion_block(block):
        for n in block.nodes():
            for blk in n.blocks():
                fusion_block(blk)

        unsupported_nodes = _get_mlir_unsupported(block)

        _ = support_fusion_group.supported_node_fusion(graph, block, unsupported_nodes, support_number_ios=True)

    with tools.trust_tracing_shape():
        fusion_block(graph)
        _disc_engine_conversion(c_module)

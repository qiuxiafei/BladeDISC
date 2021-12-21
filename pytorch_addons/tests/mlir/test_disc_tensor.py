import torch
import unittest

from tests.mlir.testing_utils import DiscTestCase


class TestDiscTensor(DiscTestCase):
    def test_tensor_cat(self):
        @torch.jit.script
        def tensor_cat(x, y, z):
            return torch.cat([x, y, z], dim=1)

        x = torch.randn([2, 1, 4, 4]).to(self.device)
        y = torch.randn([2, 2, 4, 4]).to(self.device)
        z = torch.randn([2, 3, 4, 4]).to(self.device)
        test_data = (x, y, z)
        self._test_cvt_to_disc(tensor_cat, test_data)

        z = torch.randn([2, 0, 4, 4]).to(self.device)
        test_data = (x, y, z)
        self._test_cvt_to_disc(tensor_cat, test_data)

        x = torch.randint(3, [2, 1, 4, 4]).to(self.device)
        y = torch.randint(3, [2, 2, 4, 4]).to(self.device)
        z = torch.randint(3, [2, 3, 4, 4]).to(self.device)
        test_data = (x, y, z)
        self._test_cvt_to_disc(tensor_cat, test_data)

        z = torch.randint(3, [2, 0, 4, 4]).to(self.device)
        test_data = (x, y, z)
        self._test_cvt_to_disc(tensor_cat, test_data)

    def test_aten_item(self):
        @torch.jit.script
        def test_item(tensor):
            x = int(tensor.item())
            return torch.tensor(x)

        # TODO: aten:Int only support int32_t
        self._test_cvt_to_disc(test_item, (torch.tensor((1 << 31) - 1, dtype=torch.int64),))
        self._test_cvt_to_disc(test_item, (torch.tensor(-2),))


if __name__ == "__main__":
    unittest.main()

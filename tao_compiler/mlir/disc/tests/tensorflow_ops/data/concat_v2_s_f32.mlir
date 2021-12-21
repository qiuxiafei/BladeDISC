module attributes {tf.versions = {bad_consumers = [], min_consumer = 0 : i32, producer = 0 : i32}} {
  func @main(%arg0: tensor<10x112xf32>, %arg1: tensor<10x112xf32>, %arg2: tensor<10x112xf32>) -> tensor<10x336xf32> attributes {tf.entry_function = {inputs = "{{INPUTS}}", outputs = "{{OUTPUTS}}", input_placements="{{INPUT_PLACEMENTS}}", output_placements="{{OUTPUT_PLACEMENTS}}"}} {
    %graph = tf_executor.graph {
      %0:2 = tf_executor.island wraps "tf.Const"() {value = dense<1> : tensor<i32>} : () -> tensor<i32>
      %2:2 = tf_executor.island wraps "tf.ConcatV2"(%arg0, %arg1, %arg2, %0) : (tensor<10x112xf32>, tensor<10x112xf32>, tensor<10x112xf32>, tensor<i32>) -> tensor<10x336xf32>
      tf_executor.fetch %2 : tensor<10x336xf32>
    }
    return %graph : tensor<10x336xf32>
  }
}

module attributes {tf.versions = {bad_consumers = [], min_consumer = 0 : i32, producer = 0 : i32}} {
  func @main(%arg0: tensor<?x?x?xf32>) -> (tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>) attributes {tf.entry_function = {inputs = "{{INPUTS}}", outputs = "{{OUTPUTS}}", input_placements="{{INPUT_PLACEMENTS}}", output_placements="{{OUTPUT_PLACEMENTS}}"}} {
    %graph:4 = tf_executor.graph {
      %c0:2 = tf_executor.island wraps "tf.Const"() { value = dense<0> : tensor<i32> } : () -> tensor<i32>
      %c1:2 = tf_executor.island wraps "tf.Const"() { value = dense<1> : tensor<i32> } : () -> tensor<i32>
      %c2:2 = tf_executor.island wraps "tf.Const"() { value = dense<2> : tensor<i32> } : () -> tensor<i32>
      %c3:2 = tf_executor.island wraps "tf.Const"() { value = dense<3> : tensor<i32> } : () -> tensor<i32>
      %0:2 = tf_executor.island wraps "tf.ExpandDims"(%arg0, %c0) : (tensor<?x?x?xf32>, tensor<i32>) -> (tensor<?x?x?x?xf32>)
      %1:2 = tf_executor.island wraps "tf.ExpandDims"(%arg0, %c1) : (tensor<?x?x?xf32>, tensor<i32>) -> (tensor<?x?x?x?xf32>)
      %2:2 = tf_executor.island wraps "tf.ExpandDims"(%arg0, %c2) : (tensor<?x?x?xf32>, tensor<i32>) -> (tensor<?x?x?x?xf32>)
      %3:2 = tf_executor.island wraps "tf.ExpandDims"(%arg0, %c3) : (tensor<?x?x?xf32>, tensor<i32>) -> (tensor<?x?x?x?xf32>)
      tf_executor.fetch %0, %1, %2, %3 :  tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>
    }
    return %graph#0, %graph#1, %graph#2, %graph#3 : tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>, tensor<?x?x?x?xf32>
  }
}

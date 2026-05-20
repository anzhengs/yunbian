#coding=utf-8
# ✅ 删除了报错的旧版 import tensorflow_core... 
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
import os
import numpy as np  # 新增：用于数据处理

log = 'log2/'

def lenet5(resourceid):
    with tf.device('/cpu:%d'%resourceid):
        x = tf.placeholder('float', shape=[None, 28*28])
        y_true = tf.placeholder('float', shape=[None, 10])
        x_image = tf.reshape(x, [-1, 28, 28, 1])

        def weights(shape):
            return tf.get_variable(name="weights", shape=shape, initializer=tf.truncated_normal_initializer(mean=0, stddev=0.1))


        def bias(shape):
            return tf.get_variable(name="bias", shape=shape, initializer=tf.constant_initializer(0.1))

        def conv2d(x, W):
            return tf.nn.conv2d(input=x, filter=W, strides=[1, 1, 1, 1], padding='SAME')


        def max_pool_2x2(x):
            return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

        with tf.variable_scope('c1') :
        # 1 layer: 卷积+池化层
            w_conv1 = weights([5, 5, 1, 6])  #构建出卷积核的大小
            b_conv1 = bias([6])  
            h_conv1 = tf.nn.relu(conv2d(x_image, w_conv1)+b_conv1)
            h_pool1 = max_pool_2x2(h_conv1)
        with tf.variable_scope('c2'):
        # 2 layer: 卷积+池化层
            w_conv2 = weights([5, 5, 6, 16])
            b_conv2 = bias([16])
            h_conv2 = tf.nn.relu(conv2d(h_pool1, w_conv2)+b_conv2)
            h_pool2 = max_pool_2x2(h_conv2) 
            h_pool2_flat = tf.reshape(h_pool2, [-1, 7*7*16])
        with tf.variable_scope('f1'):
        # 3 layer: 全连接
            w_fc1 = weights([7*7*16, 120])
            b_fc1 = bias([120])
            h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, w_fc1)+b_fc1)
        with tf.variable_scope('f2'):
        # 4 layer: 全连接
            w_fc2 = weights([120, 84])
            b_fc2 = bias([84])
            h_fc2 = tf.nn.relu(tf.matmul(h_fc1, w_fc2)+b_fc2)
        with tf.variable_scope('f3'):
        # 4 layer: 全连接
            w_fc3 = weights([84, 10])
            b_fc3 = bias([10])
            h_fc3=tf.matmul(h_fc2, w_fc3)+b_fc3
         
        h_fc3 = tf.nn.softmax(h_fc3,name='h_fc3')
        loss = -tf.reduce_sum(y_true * tf.log(h_fc3))
        correct_prediction = tf.equal(tf.argmax(h_fc3, 1), tf.argmax(y_true, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, 'float'))
        global_step = tf.Variable(0)
        learning_rate = tf.train.exponential_decay(1e-4, global_step, 500, 0.96, staircase=False)
        train_step = tf.train.AdamOptimizer(learning_rate).minimize(loss,global_step=global_step)
    return train_step, x, y_true, h_fc3, accuracy,loss,learning_rate

if __name__=='__main__':
    sess = tf.InteractiveSession()
    train_step, x, y_true, h_fc3,accuracy,loss,learning_rate=lenet5(0)

    tf.summary.scalar("loss", loss)
    tf.summary.scalar("lr", learning_rate)
    merged = tf.summary.merge_all()

    # ✅ 修改：使用 TF2 兼容的 Keras 接口加载数据，替代原 input_data
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    
    # 数据预处理：归一化 + One-Hot 编码
    x_train = x_train / 255.0
    x_test = x_test / 255.0
    y_train = np.eye(10)[y_train]
    y_test = np.eye(10)[y_test]

    # 模拟原来的 input_data.read_data_sets 返回的对象结构
    class DataSets:
        class Train:
            def __init__(self, images, labels):
                self.images = images.reshape(-1, 28*28)
                self.labels = labels
                self._index_in_epoch = 0
            def next_batch(self, batch_size):
                start = self._index_in_epoch
                self._index_in_epoch += batch_size
                if self._index_in_epoch > len(self.images):
                    self._index_in_epoch = batch_size
                    start = 0
                end = self._index_in_epoch
                return self.images[start:end], self.labels[start:end]
        
        def __init__(self, train_images, train_labels, test_images, test_labels):
            self.train = self.Train(train_images, train_labels)
            self.test = self.Train(test_images, test_labels)
            self.test.images = test_images.reshape(-1, 28*28)
            self.test.labels = test_labels

    mnist = DataSets(x_train, y_train, x_test, y_test)
    # ✅ 修改结束

    sess.run(tf.global_variables_initializer())

    writer = tf.summary.FileWriter("log_loss/", sess.graph)

    saver=tf.train.Saver()
    
    for i in range(10000):
        batch = mnist.train.next_batch(50)
        Writer_loss_and_lr,lossES,_=sess.run([merged,loss,train_step], feed_dict={x: batch[0], y_true: batch[1]})
        if i%100 == 0:
            writer.add_summary(Writer_loss_and_lr,i)
            train_accuracy = accuracy.eval(session=sess, feed_dict={x: batch[0], y_true: batch[1]})
            print('step {}, training accuracy: {},loss:{}'.format(i, train_accuracy,lossES))
            
            check= os.path.join(log, "model.ckpt")
            saver.save(sess, check)
    print('test accuracy: {}'.format(accuracy.eval(session=sess, feed_dict={x: mnist.test.images, y_true: mnist.test.labels})))
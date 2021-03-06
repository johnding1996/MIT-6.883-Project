import tensorflow as tf
import keras
from keras.models import Model, Sequential
from keras.layers import Input, Conv2D, MaxPooling2D, Dense, Dropout, Activation, Flatten
from keras.layers import Convolution2D, ZeroPadding2D, Activation, Add, Convolution2DTranspose
from keras_contrib.layers.normalization import InstanceNormalization
from keras.layers import Input, ZeroPadding2D, Convolution2D, LeakyReLU, Flatten, Dense, Add
from keras.optimizers import Adam
from keras import backend as K


def MSE(y_true, y_pred):
    return K.mean(K.square(y_pred - y_true), axis=-1)


def Adv(y_true, y_pred):
    target = K.sum(y_true * y_pred, axis=-1)
    other = K.max((1 - y_true) * y_pred, axis=-1)
    return K.maximum(other - target, 0)


def Hinge(c):
    def loss(y_true, y_pred):
        return  K.maximum(MSE(y_true, y_pred) - c, 0)
    return loss


def AdvGAN(input_shape, classifier_name, alpha, beta):
    G = generator(input_shape)
    D = discriminator(input_shape)
    F = keras.models.load_model('./models/Classifier-' + classifier_name + '.h5')
    ipt = Input(input_shape)
    perturbation = G(ipt)
    adversary = Add()([ipt, perturbation])
    D.trainable = False
    F.trainable = False
    judge = D(adversary)
    scores = F(adversary)

    GAN = Model(ipt, [judge, scores, perturbation])
    GAN.compile(optimizer='adam',
                loss=[MSE, Adv, Hinge(0.3/255)],
                loss_weights=[1, alpha, beta])
    return GAN, G, D, F

def AdvGAN_APEGANClassifier(input_shape, classifier_name, alpha1, alpha2, beta):
    G = generator(input_shape)
    D = discriminator(input_shape)
    F = keras.models.load_model('./models/Classifier-' + classifier_name + '.h5')
    APEG = keras.models.load_model('./models/APEGAN-AdvGANAllTarget-G.h5')
    ipt = Input(input_shape)
    perturbation = G(ipt)
    adversary = Add()([ipt, perturbation])
    D.trainable = False
    APEG.trainable = False
    F.trainable = False
    judge = D(adversary)
    scores1 = F(adversary)
    scores2 = F(APEG(adversary))

    GAN = Model(ipt, [judge, scores1, scores2, perturbation])
    GAN.compile(optimizer='adam',
                loss=[MSE, Adv, Adv, Hinge(0.3/255)],
                loss_weights=[1, alpha1, alpha2, beta])
    return GAN, G, D, APEG, F


def generator(input_shape=[28,28,1]):
    def conv__inst_norm__relu(x_input, filters, kernel_size=(3, 3), stride=1):
        l = ZeroPadding2D()(x_input)
        l = Convolution2D(filters=filters, kernel_size=(3, 3), strides=stride, activation='linear')(l)
        l = InstanceNormalization()(l)
        l = Activation('relu')(l)
        return l

    def res__block(x_input, filters, kernel_size=(3, 3), stride=1):
        l = ZeroPadding2D()(x_input)
        l = Convolution2D(filters=filters,
                          kernel_size=kernel_size,
                          strides=stride, )(l)
        l = InstanceNormalization()(l)
        l = Activation('relu')(l)

        l = ZeroPadding2D()(l)
        l = Convolution2D(filters=filters,
                          kernel_size=kernel_size,
                          strides=stride, )(l)
        l = InstanceNormalization()(l)
        merged = Add()([x_input, l])
        return merged

    def trans_conv__inst_norm__relu(x_input, filters, kernel_size=(3, 3), stride=2):
        l = Convolution2DTranspose(filters=filters, kernel_size=kernel_size, strides=stride, activation='linear',
                                   padding='same')(x_input)
        l = InstanceNormalization()(l)
        l = Activation('relu')(l)
        return l

    m_in = Input(shape=input_shape)
    m = conv__inst_norm__relu(m_in, filters=8, stride=1)
    m = conv__inst_norm__relu(m, filters=16, stride=2)
    m = conv__inst_norm__relu(m, filters=32, stride=2)
    m = res__block(m, filters=32)
    m = res__block(m, filters=32)
    m = res__block(m, filters=32)
    m = res__block(m, filters=32)
    m = trans_conv__inst_norm__relu(m, filters=16, stride=2)
    m = trans_conv__inst_norm__relu(m, filters=8, stride=2)
    m_out = conv__inst_norm__relu(m, filters=1, stride=1)
    M = Model(m_in, m_out)
    M.compile(optimizer='adam', loss='mean_squared_error')
    return M


def discriminator(input_shape=[28, 28, 1]):
    m_in = Input(shape=input_shape)
    m = ZeroPadding2D()(m_in)
    m = Convolution2D(filters=8,
                      kernel_size=(4, 4),
                      strides=2)(m)
    m = InstanceNormalization()(m)
    m = LeakyReLU(0.2)(m)
    m = ZeroPadding2D()(m)
    m = Convolution2D(filters=16,
                      kernel_size=(4, 4),
                      strides=2)(m)
    m = InstanceNormalization()(m)
    m = LeakyReLU(0.2)(m)
    m = ZeroPadding2D()(m)
    m = Convolution2D(filters=32,
                      kernel_size=(4, 4),
                      strides=2)(m)
    m = InstanceNormalization()(m)
    m = LeakyReLU(0.2)(m)
    m = Flatten()(m)
    m_out = Dense(1, activation='sigmoid')(m)
    M = Model(m_in, m_out)
    M.compile(optimizer='adam', loss='mean_squared_error')
    return M

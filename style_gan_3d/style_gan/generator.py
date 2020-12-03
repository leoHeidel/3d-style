import tensorflow as tf
import tensorflow.keras as keras

import style_gan_3d


def to_rgb(inp, style, im_size):
    current_size = inp.shape[2]
    x = style_gan_3d.style_gan.conv_mod.Conv2DMod(3, 1, kernel_initializer = keras.initializers.VarianceScaling(200/current_size), 
                              demod = False)([inp, style])
    factor = im_size // current_size
    x = keras.layers.UpSampling2D(size=(factor, factor), interpolation='bilinear')(x)
    return x

def g_block(x, input_style, input_noise, nb_filters, im_size, upsampling = True):
    input_filters = x.shape[-1]
    if upsampling:
        x = keras.layers.UpSampling2D(interpolation='bilinear')(x)
    
    current_size = x.shape[2]
    rgb_style = keras.layers.Dense(nb_filters, kernel_initializer = keras.initializers.VarianceScaling(200/current_size))(input_style)
    style = keras.layers.Dense(input_filters, kernel_initializer = 'he_uniform')(input_style)
    

    noise_cropped = input_noise[:,:current_size, :current_size] 
    d = keras.layers.Dense(nb_filters, kernel_initializer='zeros')(noise_cropped)

    x = style_gan_3d.style_gan.conv_mod.Conv2DMod(filters=nb_filters, kernel_size = 3, padding = 'same', kernel_initializer = 'he_uniform')([x, style])
    x = keras.layers.add([x, d])
    x = keras.layers.LeakyReLU(0.2)(x)

    style = keras.layers.Dense(nb_filters, kernel_initializer = 'he_uniform')(input_style)
    d = keras.layers.Dense(nb_filters, kernel_initializer = 'zeros')(noise_cropped)

    x = style_gan_3d.style_gan.conv_mod.Conv2DMod(filters = nb_filters, kernel_size = 3, padding = 'same', kernel_initializer = 'he_uniform')([x, style])
    x = keras.layers.add([x, d])
    x = keras.layers.LeakyReLU(0.2)(x)

    return x, to_rgb(x, rgb_style, im_size)

def make_style_map(model):
    S = keras.models.Sequential()
    S.add(keras.layers.Dense(model.latent_size, input_shape = [model.latent_size]))
    for i in range(model.nb_style_mapper_layer):
        S.add(keras.layers.LeakyReLU(0.2))
        S.add(keras.layers.Dense(model.latent_size))
    return S

def make_generator(model):
    start_dim = model.im_size // (2**(model.n_layers-1))
    
    inp_seed = keras.layers.Input([start_dim, start_dim, 4*model.channels])
    inp_style = keras.layers.Input([model.n_layers, model.latent_size])
    inp_noise = keras.layers.Input([model.im_size, model.im_size, 1])

    outs = []
    x = inp_seed

    for i, channels_mult in enumerate(model.channels_mult_list[:model.n_layers][::-1]):
        x, r = g_block(x, inp_style[:,i], inp_noise, channels_mult * model.channels, model.im_size, upsampling = (i!=0))  
        outs.append(r)
    x = keras.layers.add(outs)
    x = x/2 + 0.5 #Use values centered around 0, but normalize to [0, 1], providing better initialization
    return keras.models.Model(inputs = [inp_seed, inp_style, inp_noise], outputs = x)
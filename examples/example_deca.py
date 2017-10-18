# Example how to use the deca on T#

## Set all deca channels to the same value (e.g 0)
deca.set_all(0)

## Set the source channel to the same value as well:
deca.set_all(0, set_dcbias=True)

## Set source bias
deca.dcbias(2e-3)

## Query voltage on left cutter
v_l_cut = deca.lcut()
print('Voltage on left cutter: {}'.format(v_l_cut))

## Check voltage on unused channel (a channel not listed in sample.config)
channel_to_test = 17
voltage = deca.channels[channel_to_test].volt()
print('Voltage on channel {}: {}'.format(channel_to_test, voltage))

## Set voltage of a channel not listed in sample.config:
channel_to_test = 16
voltage = 2
deca.channels[channel_to_test].volt(voltage)
print('New voltage on channel {}: {}'.format(channel_to_test,
                        deca.channels[channel_to_test].volt()))


## Left cutter
print('left cutter: {}'.format(deca.lcut())

## right cutter
print('left cutter: {}'.format(deca.rcut()))

## central cutter aka Josephson junction (jj)
print('central cutter: {}'.format(deca.jj())

## right plunger
print('right plunger: {}'.format(deca.rplg())

## left plunger
print('left plunger: {}'.format(deca.lplg())
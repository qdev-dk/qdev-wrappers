from broadbean import PulseAtoms

# atom elements
def const(val, SR, npts):
    return PulseAtoms.ramp(val, val, SR, npts)

def zero(SR, npts):
    return PulseAtoms.ramp(0, 0, SR, npts)

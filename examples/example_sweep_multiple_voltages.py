# Example how to sweep multiple deca voltages at the same time 
# There are two possible ways: Using a lambda function or qcodes' combined
# parameter

## Using a lambda function

### We need to create a qcodes task. It is a function like object which will be 
### executed at each iteration. 
### If the task is to set another gate voltage, depending on whatever parameters
### we want, we have a compensated gate.

### No compensation/set the same votlage on e.g lcut and rcut:

set_lcut = lambda: deca.lcut()
### rcut should be at the same voltage as lcut
compensation_task = qc.Task(deca.rcut.set, set_lcut)

### Make sure to list the compensation before the instruments to measure if
### the measurment should happen after both voltages are set.
plot, data = do1d(deca.lcut, 0, 1, 100, 0.1, compensation_task, lockin_2.g)


### If we want to compensate the central cutter (jj) while sweeping for ex the 
### left cutter we do the following. 
### (We choose to comensate as v_jj = 0.2 + 0.1*v_lcut)
 
compensation_relation = lambda: 0.2 + 0.1 * deca.lcut()
compensation_task = qc.Task(deca.jj.set, compensation_relation)

plot, data = do1d(deca.lcut, 0, 1, 100, 0.1, compensation_task, lockin_2.g)


## Using qcodes' combined parameter

### Have a look here:
### https://github.com/QCoDeS/Qcodes/blob/master/docs/examples/Combined%20Parameters.ipynb
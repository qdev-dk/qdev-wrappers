from conductance_measurements import do2Dconductance
import time

# simple example of running a 2d conductance measurement

start = time.time()
plot, data = do2Dconductance(qdac.channels.chan1.v,
                0,
                1,
                10,
                qdac.channels.chan2.v,
                0,
                0.09    ,
                10,
                lockin,
                delay=0.007)
end = time.time()

print("Conductance example took {} s".format(end-start))
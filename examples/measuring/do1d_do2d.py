# do1d and do2d examples

## Measure several parameters at the same time:
## (Just list all parameters you want to measure.)
do1d(deca.lcut, 0, 1, 100, 0.1, lockin_2.g, lockin_2.X, lockin_2.resistance)

## Same for 2D:
do2d(deca.lcut, 0, 1, 100, 0.1, deca.rcut, 0, 1, 100, 0.1, 
             lockin_2.g, lockin_2.X, lockin_2.resistance)



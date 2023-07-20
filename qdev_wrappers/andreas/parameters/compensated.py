from qcodes.instrument.parameter import Parameter

class CompensatedParameter(Parameter):
    def __init__(self, name, label, unit, prime_parameter, second_parameter, point_1, point_2):
        super().__init__(name=name, label=label, unit=unit)
        self.prime_parameter = prime_parameter
        self.second_parameter = second_parameter
        self.slope = (point_1[1]-point_2[1])/(point_1[0]-point_2[0])
        self.intercept = point_1[1] - self.slope * point_1[0]

    def set_raw(self, value):
        self.prime_parameter(value)
        self.second_parameter(self.slope*value+self.intercept)

    def get_raw(self):
        return self.prime_parameter()

class CompensatedParameterDouble(Parameter):
    def __init__(self, name, label, unit, prime_parameter, second_parameter_1, point_1_a, point_1_b,
                 second_parameter_2, point_2_a, point_2_b):
        super().__init__(name=name, label=label, unit=unit)
        self.parameters = [prime_parameter, second_parameter_1, second_parameter_2]
        self.points_a = [point_1_a, point_2_a]
        self.points_b = [point_1_b, point_2_b]
        self.slopes = [1]
        self.intercepts = [0]
        for i in range(2):
            point_a = self.points_a[i]
            point_b = self.points_b[i]
            slope = (point_a[1]-point_b[1])/(point_a[0]-point_b[0])
            intercept = point_a[1] - slope * point_a[0]
            self.slopes.append(slope)
            self.intercepts.append(intercept)

    def set_raw(self, value):
        for i in range(3):
            self.parameters[i](self.slopes[i]*value+self.intercepts[i])

    def get_raw(self):
        return self.parameters[0]()

class CompensatedParameterTriple(Parameter):
    def __init__(self, name, label, unit, prime_parameter, second_parameter_1, point_1_a, point_1_b,
                 second_parameter_2, point_2_a, point_2_b,
                 second_parameter_3, point_3_a, point_3_b):
        super().__init__(name=name, label=label, unit=unit)
        self.parameters = [prime_parameter, second_parameter_1, second_parameter_2, second_parameter_3]
        self.points_a = [point_1_a, point_2_a, point_3_a]
        self.points_b = [point_1_b, point_2_b, point_3_b]
        self.slopes = [1]
        self.intercepts = [0]
        for i in range(3):
            point_a = self.points_a[i]
            point_b = self.points_b[i]
            slope = (point_a[1]-point_b[1])/(point_a[0]-point_b[0])
            intercept = point_a[1] - slope * point_a[0]
            self.slopes.append(slope)
            self.intercepts.append(intercept)

    def set_raw(self, value):
        for i in range(4):
            self.parameters[i](self.slopes[i]*value+self.intercepts[i])

    def get_raw(self):
        return self.parameters[0]()

class CompensatedParameterFunction(Parameter):
    def __init__(self, name, label, unit, prime_parameter, second_parameter, func):
        super().__init__(name=name, label=label, unit=unit)
        self.parameters = [prime_parameter, second_parameter]
        self.func = func
    

    def set_raw(self, value):
        self.parameters[0](value)
        self.parameters[1](self.func(value))

    def get_raw(self):
        return self.parameters[0]()

class CompensatedParameterQuadruple(Parameter):
    def __init__(self, name, label, unit, prime_parameter, second_parameter_1, point_1_a, point_1_b,
                 second_parameter_2, point_2_a, point_2_b,
                 second_parameter_3, point_3_a, point_3_b,
                 second_parameter_4, point_4_a, point_4_b):
        super().__init__(name=name, label=label, unit=unit)
        self.parameters = [prime_parameter, second_parameter_1, second_parameter_2, second_parameter_3, second_parameter_4]
        self.points_a = [point_1_a, point_2_a, point_3_a, point_4_a]
        self.points_b = [point_1_b, point_2_b, point_3_b, point_4_b]
        self.slopes = [1]
        self.intercepts = [0]
        for i in range(4):
            point_a = self.points_a[i]
            point_b = self.points_b[i]
            slope = (point_a[1]-point_b[1])/(point_a[0]-point_b[0])
            intercept = point_a[1] - slope * point_a[0]
            self.slopes.append(slope)
            self.intercepts.append(intercept)

    def set_raw(self, value):
        for i in range(5):
            self.parameters[i](self.slopes[i]*value+self.intercepts[i])

    def get_raw(self):
        return self.parameters[0]()

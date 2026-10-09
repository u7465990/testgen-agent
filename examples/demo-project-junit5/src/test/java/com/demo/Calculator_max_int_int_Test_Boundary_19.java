package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_max_int_int_Test_Boundary_19 {


    @Test
    public void testMaxWithBoundaryA() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 5;
        int result = calculator.max(a, b);
        Assertions.assertEquals(5, result, "max(0, 5) should return the larger value 5");
    }

}

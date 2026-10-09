package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_multiply_int_int_Test_Boundary_15 {


    @Test
    public void testMultiplyWithBoundaryZeroForFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 7;
        int expected = 0;
        int actual = calculator.multiply(a, b);
        Assertions.assertEquals(expected, actual, "Multiplying 0 by 7 should yield 0");
    }

}

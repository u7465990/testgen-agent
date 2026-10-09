package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_subtract_int_int_Test_Boundary_13 {

    @Test
    public void testSubtractWithZeroAsFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 10;
        int expected = -10;
        int actual = calculator.subtract(a, b);
        Assertions.assertEquals(expected, actual, "0 - 10 should be -10");
    }

}

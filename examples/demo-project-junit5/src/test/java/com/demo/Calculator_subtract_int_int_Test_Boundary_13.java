package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_subtract_int_int_Test_Boundary_13 {


    @Test
    public void testSubtractWithZeroAsFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 1;
        int expected = -1;
        int actual = calculator.subtract(a, b);
        assertEquals(expected, actual, "subtract(0, 1) should return -1");
    }

}

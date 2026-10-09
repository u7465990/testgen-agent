package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_divide_int_int_Test_Boundary_17 {


    @Test
    public void testDivideWithZeroDividend() {
        Calculator calculator = new Calculator();

        int a = 0;
        int b = 1;

        int result = calculator.divide(a, b);

        Assertions.assertEquals(0, result, "0 / 1 should equal 0");
    }

}

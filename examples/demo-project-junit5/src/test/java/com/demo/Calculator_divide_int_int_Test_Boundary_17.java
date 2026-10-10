package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_divide_int_int_Test_Boundary_17 {


    @Test
    public void testDivideWithZeroDividend() {
        Calculator calculator = new Calculator();
        int result = calculator.divide(0, 1);
        assertEquals(0, result, "Dividing zero by a non-zero value should yield zero");
    }

}

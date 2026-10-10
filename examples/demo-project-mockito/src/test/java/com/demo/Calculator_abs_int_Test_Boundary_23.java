package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_abs_int_Test_Boundary_23 {


    @Test
    public void testAbsWithZeroBoundary() {
        Calculator calculator = new Calculator();
        int result = calculator.abs(0);
        Assert.assertEquals(0, result);
    }

}

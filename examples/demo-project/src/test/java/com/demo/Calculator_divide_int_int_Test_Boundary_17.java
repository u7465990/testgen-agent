package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_divide_int_int_Test_Boundary_17 {


    @Test
    public void divide_withZeroDividend_returnsZero() {
        Calculator calculator = new Calculator();
        Assert.assertEquals(0, calculator.divide(0, 2));
        Assert.assertEquals(0, calculator.divide(0, -5));
    }

}

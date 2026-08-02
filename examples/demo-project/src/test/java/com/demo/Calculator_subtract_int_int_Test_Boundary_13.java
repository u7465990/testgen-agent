package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_subtract_int_int_Test_Boundary_13 {


    @Test
    public void subtract_withZeroMinuend_returnsNegativeSubtrahend() {
        Calculator calculator = new Calculator();
        Assert.assertEquals(-5, calculator.subtract(0, 5));
    }

}

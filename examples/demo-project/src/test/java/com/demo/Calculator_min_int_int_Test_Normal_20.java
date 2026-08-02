package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_min_int_int_Test_Normal_20 {


    @Test
    public void min_returnsMinimumForTypicalValues() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(0, calculator.min(0, 1));
        Assert.assertEquals(-1, calculator.min(1, -1));
        Assert.assertEquals(-1, calculator.min(-1, 0));
        Assert.assertEquals(-1, calculator.min(-1, 1));
        Assert.assertEquals(0, calculator.min(-0, 0));
    }

}

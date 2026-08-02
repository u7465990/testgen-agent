package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_abs_int_Test_Normal_22 {

    @Test
    public void abs_typicalValues_returnsExpected() {
        Calculator calculator = new Calculator();
        Assert.assertEquals(0, calculator.abs(0));
        Assert.assertEquals(1, calculator.abs(1));
        Assert.assertEquals(1, calculator.abs(-1));
    }

}

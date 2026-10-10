package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_add_int_int_Test_Normal_10 {


    @Test
    public void testAddWithRepresentativeInputs() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(0, calculator.add(0, 0));
        Assert.assertEquals(1, calculator.add(0, 1));
        Assert.assertEquals(-1, calculator.add(0, -1));
        Assert.assertEquals(1, calculator.add(1, 0));
        Assert.assertEquals(2, calculator.add(1, 1));
        Assert.assertEquals(0, calculator.add(1, -1));
        Assert.assertEquals(-1, calculator.add(-1, 0));
        Assert.assertEquals(0, calculator.add(-1, 1));
        Assert.assertEquals(-2, calculator.add(-1, -1));
    }

}

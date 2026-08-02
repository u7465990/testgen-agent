package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_add_int_int_Test_Boundary_11 {

    @Test
    public void testAddWithZeroAsFirstParameter() {
        Calculator calculator = new Calculator();
        int result = calculator.add(0, 5);
        Assert.assertEquals(5, result);
    }

}

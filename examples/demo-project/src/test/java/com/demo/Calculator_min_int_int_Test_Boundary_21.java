package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_min_int_int_Test_Boundary_21 {


    @Test
    public void testMinWithABoundaryZero() {
        Calculator calculator = new Calculator();
        Assert.assertEquals(0, calculator.min(0, 0));
    }

}

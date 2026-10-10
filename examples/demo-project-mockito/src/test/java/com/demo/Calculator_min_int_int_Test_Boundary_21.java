package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_min_int_int_Test_Boundary_21 {


    @Test
    public void testMinWithBoundaryFirstParameterZero() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 5;
        int result = calculator.min(a, b);
        Assert.assertEquals(0, result);
    }

}

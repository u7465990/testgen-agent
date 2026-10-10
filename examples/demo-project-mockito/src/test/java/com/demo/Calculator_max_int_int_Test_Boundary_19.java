package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_max_int_int_Test_Boundary_19 {


    @Test
    public void testMaxWithBoundaryZeroFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 1;
        int result = calculator.max(a, b);
        Assert.assertEquals(1, result);
    }

}

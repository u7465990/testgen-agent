package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_add_int_int_Test_Boundary_11 {


    @Test
    public void testAddWithBoundaryZeroForParameterA() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 1;

        int result = calculator.add(a, b);

        Assert.assertEquals(1, result);
    }

}

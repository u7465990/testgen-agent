package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_min_int_int_Test_Boundary_21 {


    @Test
    public void testMinWithBoundaryZeroAsFirstArgument() {
        Calculator calculator = new Calculator();

        int a = 0;
        int b = 5;

        int result = calculator.min(a, b);

        Assertions.assertEquals(0, result);
    }

}

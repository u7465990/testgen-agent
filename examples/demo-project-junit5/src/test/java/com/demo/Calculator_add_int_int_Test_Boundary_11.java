package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_add_int_int_Test_Boundary_11 {


    @Test
    public void testAddWithZeroAsFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 7;
        int result = calculator.add(a, b);
        Assertions.assertEquals(7, result);
    }

}

package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_add_int_int_Test_Boundary_11 {


    @Test
    public void testAddWithBoundaryZeroForFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 5;
        int expected = 5;
        int actual = calculator.add(a, b);
        assertEquals(expected, actual);
    }

}

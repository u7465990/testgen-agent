package com.demo;

import com.demo.Calculator;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class Calculator_abs_int_Test_Boundary_23 {


    @Test
    public void testAbsBoundaryZero() {
        Calculator calculator = new Calculator();
        assertEquals(0, calculator.abs(0));
    }

}

package com.demo;

import com.demo.Calculator;
import org.junit.Test;
import static org.junit.Assert.*;

public class Calculator_divide_int_int_Test_Boundary_17 {

    @Test
    public void testDivideWithBoundaryParam0() {
        Calculator calculator = new Calculator();
        int result = calculator.divide(0, 1);
        assertEquals(0, result);
    }

}

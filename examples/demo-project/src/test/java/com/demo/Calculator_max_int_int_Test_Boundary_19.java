package com.demo;

import com.demo.Calculator;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class Calculator_max_int_int_Test_Boundary_19 {


    @Test
    public void testMaxWithBoundaryA() {
        Calculator calculator = new Calculator();
        int result = calculator.max(0, 5);
        assertEquals(5, result);
    }

}

package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_min_int_int_Test_Boundary_21 {


    @Test
    public void testMinWithBoundaryZeroForFirstParameter() {
        Calculator calculator = new Calculator();

        int a = 0;
        int b = 1;

        int result = calculator.min(a, b);

        assertEquals(0, result, "min(0, 1) should return the boundary value 0");
    }

}

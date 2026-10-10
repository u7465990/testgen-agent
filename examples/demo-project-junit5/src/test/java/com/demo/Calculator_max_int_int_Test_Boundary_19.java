package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_max_int_int_Test_Boundary_19 {


    @Test
    public void testMaxWithBoundaryZeroForFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 0;
        int result = calculator.max(a, b);
        assertEquals(0, result, "max(0, 0) should return 0");
    }

}

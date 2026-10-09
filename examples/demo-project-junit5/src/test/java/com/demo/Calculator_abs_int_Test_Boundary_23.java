package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_abs_int_Test_Boundary_23 {


    @Test
    public void testAbsWithBoundaryInputZero() {
        Calculator calculator = new Calculator();

        int result = calculator.abs(0);

        Assertions.assertEquals(0, result, "abs(0) should return 0");
    }

}

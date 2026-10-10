package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_abs_int_Test_Normal_22 {


    @Test
    public void testAbsWithTypicalValues() {
        Calculator calculator = new Calculator();

        assertEquals(0, calculator.abs(0), "abs(0) should return 0");
        assertEquals(1, calculator.abs(1), "abs(1) should return 1");
        assertEquals(1, calculator.abs(-1), "abs(-1) should return 1");
    }

}

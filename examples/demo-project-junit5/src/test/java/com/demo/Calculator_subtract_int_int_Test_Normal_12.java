package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_subtract_int_int_Test_Normal_12 {


    @Test
    public void testSubtractWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        assertEquals(0, calculator.subtract(0, 0));
        assertEquals(1, calculator.subtract(1, 0));
        assertEquals(-1, calculator.subtract(0, 1));
        assertEquals(2, calculator.subtract(1, -1));
        assertEquals(-2, calculator.subtract(-1, 1));
        assertEquals(0, calculator.subtract(-1, -1));
        assertEquals(0, calculator.subtract(1, 1));
    }

}

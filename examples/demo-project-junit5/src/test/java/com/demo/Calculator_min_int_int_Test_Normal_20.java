package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_min_int_int_Test_Normal_20 {


    @Test
    public void testMinWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        // Typical positive values: smaller first
        assertEquals(1, calculator.min(1, 2));

        // Typical positive values: smaller second
        assertEquals(1, calculator.min(2, 1));

        // Equal values
        assertEquals(0, calculator.min(0, 0));

        // Zero and one
        assertEquals(0, calculator.min(0, 1));
        assertEquals(0, calculator.min(1, 0));

        // Negative values
        assertEquals(-1, calculator.min(-1, 0));
        assertEquals(-1, calculator.min(0, -1));
        assertEquals(-1, calculator.min(-1, -1));

        // Mixed sign
        assertEquals(-1, calculator.min(-1, 1));
        assertEquals(-1, calculator.min(1, -1));
    }

}

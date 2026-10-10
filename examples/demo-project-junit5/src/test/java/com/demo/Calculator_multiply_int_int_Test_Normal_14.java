package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertAll;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_multiply_int_int_Test_Normal_14 {


    @Test
    public void testMultiplyWithTypicalValues() {
        Calculator calculator = new Calculator();

        assertAll(
            () -> assertEquals(0, calculator.multiply(0, 0), "0 * 0 should be 0"),
            () -> assertEquals(0, calculator.multiply(0, 1), "0 * 1 should be 0"),
            () -> assertEquals(0, calculator.multiply(0, -1), "0 * -1 should be 0"),
            () -> assertEquals(0, calculator.multiply(1, 0), "1 * 0 should be 0"),
            () -> assertEquals(1, calculator.multiply(1, 1), "1 * 1 should be 1"),
            () -> assertEquals(-1, calculator.multiply(1, -1), "1 * -1 should be -1"),
            () -> assertEquals(0, calculator.multiply(-1, 0), "-1 * 0 should be 0"),
            () -> assertEquals(1, calculator.multiply(-1, -1), "-1 * -1 should be 1"),
            () -> assertEquals(-1, calculator.multiply(-1, 1), "-1 * 1 should be -1")
        );
    }

}

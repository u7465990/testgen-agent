package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_multiply_int_int_Test_Normal_14 {


    @Test
    public void testMultiplyWithTypicalValues() {
        Calculator calculator = new Calculator();

        // 0 * 0 == 0
        Assertions.assertEquals(0, calculator.multiply(0, 0));

        // 1 * 1 == 1
        Assertions.assertEquals(1, calculator.multiply(1, 1));

        // -1 * 1 == -1
        Assertions.assertEquals(-1, calculator.multiply(-1, 1));

        // -1 * -1 == 1
        Assertions.assertEquals(1, calculator.multiply(-1, -1));

        // 0 * 1 == 0
        Assertions.assertEquals(0, calculator.multiply(0, 1));

        // 0 * -1 == 0
        Assertions.assertEquals(0, calculator.multiply(0, -1));
    }

}

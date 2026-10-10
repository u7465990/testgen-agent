package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_subtract_int_int_Test_Normal_12 {


    @Test
    public void testSubtractWithTypicalValues() {
        Calculator calculator = new Calculator();

        Assertions.assertAll(
                () -> Assertions.assertEquals(0, calculator.subtract(0, 0)),
                () -> Assertions.assertEquals(1, calculator.subtract(1, 0)),
                () -> Assertions.assertEquals(-1, calculator.subtract(-1, 0)),
                () -> Assertions.assertEquals(0, calculator.subtract(1, 1)),
                () -> Assertions.assertEquals(26, calculator.subtract(25, -1))
        );
    }

}

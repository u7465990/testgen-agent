package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_divide_int_int_Test_Normal_16 {

    @Test
    public void testDivideWithTypicalValues() {
        Calculator calculator = new Calculator();

        Assertions.assertEquals(0, calculator.divide(0, 1));
        Assertions.assertEquals(1, calculator.divide(1, 1));
        Assertions.assertEquals(-1, calculator.divide(-1, 1));
        Assertions.assertEquals(0, calculator.divide(0, -1));
        Assertions.assertEquals(-1, calculator.divide(1, -1));
        Assertions.assertEquals(1, calculator.divide(-1, -1));
    }

}

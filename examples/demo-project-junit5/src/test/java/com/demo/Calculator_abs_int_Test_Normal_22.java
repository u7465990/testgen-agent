package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_abs_int_Test_Normal_22 {


    @Test
    public void testAbsWithTypicalValues() {
        Calculator calculator = new Calculator();

        int resultZero = calculator.abs(0);
        Assertions.assertEquals(0, resultZero);

        int resultOne = calculator.abs(1);
        Assertions.assertEquals(1, resultOne);

        int resultNegativeOne = calculator.abs(-1);
        Assertions.assertEquals(1, resultNegativeOne);
    }

}
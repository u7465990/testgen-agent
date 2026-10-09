package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_divide_int_int_Test_Normal_16 {


    @Test
    public void testDivideWithRepresentativeValidInputs() {
        Calculator calculator = new Calculator();

        int resultZeroNumerator = calculator.divide(0, 1);
        Assertions.assertEquals(0, resultZeroNumerator);

        int resultPositiveByOne = calculator.divide(1, 1);
        Assertions.assertEquals(1, resultPositiveByOne);

        int resultNegativeByOne = calculator.divide(-1, 1);
        Assertions.assertEquals(-1, resultNegativeByOne);

        int resultZeroDividendNegativeDivisor = calculator.divide(0, -1);
        Assertions.assertEquals(0, resultZeroDividendNegativeDivisor);

        int resultPositiveDivision = calculator.divide(6, 2);
        Assertions.assertEquals(3, resultPositiveDivision);

        int resultNegativeDivision = calculator.divide(-6, 2);
        Assertions.assertEquals(-3, resultNegativeDivision);

        int resultBothNegative = calculator.divide(-6, -2);
        Assertions.assertEquals(3, resultBothNegative);
    }

}

package com.demo;

import com.demo.Calculator;
import com.demo.Calculator.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Assertions.*;

public class Calculator_max_int_int_Test_Normal_18 {


    @Test
    public void testMaxWithTypicalValues() {
        Calculator calculator = new Calculator();

        int result00 = calculator.max(0, 0);
        Assertions.assertEquals(0, result00, "max(0, 0) should return 0");

        int result10 = calculator.max(1, 0);
        Assertions.assertEquals(1, result10, "max(1, 0) should return 1");

        int result01 = calculator.max(0, 1);
        Assertions.assertEquals(1, result01, "max(0, 1) should return 1");

        int resultNeg10 = calculator.max(-1, 0);
        Assertions.assertEquals(0, resultNeg10, "max(-1, 0) should return 0");

        int result0Neg1 = calculator.max(0, -1);
        Assertions.assertEquals(0, result0Neg1, "max(0, -1) should return 0");

        int resultNeg11 = calculator.max(-1, 1);
        Assertions.assertEquals(1, resultNeg11, "max(-1, 1) should return 1");

        int result1Neg1 = calculator.max(1, -1);
        Assertions.assertEquals(1, result1Neg1, "max(1, -1) should return 1");

        int resultNeg1Neg1 = calculator.max(-1, -1);
        Assertions.assertEquals(-1, resultNeg1Neg1, "max(-1, -1) should return -1");
    }

}

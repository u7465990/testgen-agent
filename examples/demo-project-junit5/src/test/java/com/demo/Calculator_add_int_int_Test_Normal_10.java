package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class Calculator_add_int_int_Test_Normal_10 {


    @Test
    public void testAddWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        // 0 + 0 = 0
        int result1 = calculator.add(0, 0);
        Assertions.assertEquals(0, result1, "0 + 0 should equal 0");

        // 1 + 1 = 2
        int result2 = calculator.add(1, 1);
        Assertions.assertEquals(2, result2, "1 + 1 should equal 2");

        // -1 + -1 = -2
        int result3 = calculator.add(-1, -1);
        Assertions.assertEquals(-2, result3, "-1 + -1 should equal -2");

        // 0 + 1 = 1
        int result4 = calculator.add(0, 1);
        Assertions.assertEquals(1, result4, "0 + 1 should equal 1");

        // 1 + -1 = 0
        int result5 = calculator.add(1, -1);
        Assertions.assertEquals(0, result5, "1 + -1 should equal 0");

        // -1 + 0 = -1
        int result6 = calculator.add(-1, 0);
        Assertions.assertEquals(-1, result6, "-1 + 0 should equal -1");
    }

}

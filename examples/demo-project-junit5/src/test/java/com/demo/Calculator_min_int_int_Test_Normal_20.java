package com.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import com.demo.Calculator;
import org.junit.jupiter.api.Test;

public class Calculator_min_int_int_Test_Normal_20 {


    @Test
    public void testMinWithTypicalValues() {
        Calculator calculator = new Calculator();

        // Case 1: a = 0, b = 1 -> min is 0
        int result1 = calculator.min(0, 1);
        assertEquals(0, result1);

        // Case 2: a = -1, b = 0 -> min is -1
        int result2 = calculator.min(-1, 0);
        assertEquals(-1, result2);

        // Case 3: a = 1, b = -1 -> min is -1
        int result3 = calculator.min(1, -1);
        assertEquals(-1, result3);

        // Case 4: a = 0, b = -1 -> min is -1
        int result4 = calculator.min(0, -1);
        assertEquals(-1, result4);
    }

}

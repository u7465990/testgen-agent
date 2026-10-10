package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_max_int_int_Test_Normal_18 {


    @Test
    public void testMaxWithTypicalValues() {
        Calculator calculator = new Calculator();

        assertEquals(1, calculator.max(0, 1));
        assertEquals(0, calculator.max(0, -1));
        assertEquals(1, calculator.max(1, 0));
        assertEquals(0, calculator.max(-1, 0));
        assertEquals(1, calculator.max(-1, 1));
        assertEquals(1, calculator.max(1, -1));
    }

}

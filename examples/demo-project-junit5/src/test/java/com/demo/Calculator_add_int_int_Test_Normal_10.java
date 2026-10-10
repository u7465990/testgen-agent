package com.demo;

import com.demo.Calculator;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class Calculator_add_int_int_Test_Normal_10 {


    @Test
    public void testAddWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        assertEquals(0, calculator.add(0, 0));
        assertEquals(1, calculator.add(1, 0));
        assertEquals(-1, calculator.add(-1, 0));
        assertEquals(0, calculator.add(1, -1));
        assertEquals(2, calculator.add(1, 1));
        assertEquals(0, calculator.add(-1, 1));
        assertEquals(-2, calculator.add(-1, -1));
    }

}

package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_countOccurrences_Str_Char_Test_Boundary_39 {


    @Test
    public void testCountOccurrencesWithNullString() {
        String s = null;
        char c = 'a';
        int result = TextUtil.countOccurrences(s, c);
        Assertions.assertEquals(0, result);
    }

}

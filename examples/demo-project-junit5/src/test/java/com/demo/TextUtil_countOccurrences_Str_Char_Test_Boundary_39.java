package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class TextUtil_countOccurrences_Str_Char_Test_Boundary_39 {


    @Test
    public void testCountOccurrencesWithNullString() {
        char c = 'a';
        int result = TextUtil.countOccurrences(null, c);
        assertEquals(0, result, "countOccurrences should return 0 when the input string is null");
    }

}

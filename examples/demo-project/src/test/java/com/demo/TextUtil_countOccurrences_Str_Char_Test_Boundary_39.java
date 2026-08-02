package com.demo;

import com.demo.TextUtil;
import static org.junit.Assert.assertEquals;
import org.junit.Test;

public class TextUtil_countOccurrences_Str_Char_Test_Boundary_39 {


    @Test
    public void testCountOccurrencesWithNullString() {
        assertEquals(0, TextUtil.countOccurrences(null, 'a'));
    }

}

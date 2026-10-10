package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertAll;

public class TextUtil_countOccurrences_Str_Char_Test_Normal_38 {


    @Test
    public void testCountOccurrencesWithTypicalValues() {
        assertAll(
                () -> assertEquals(0, TextUtil.countOccurrences("test", 'a')),
                () -> assertEquals(2, TextUtil.countOccurrences("test", 't')),
                () -> assertEquals(1, TextUtil.countOccurrences("test", 'e')),
                () -> assertEquals(0, TextUtil.countOccurrences("", 'a')),
                () -> assertEquals(3, TextUtil.countOccurrences("banana", 'a'))
        );
    }

}

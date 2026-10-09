package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_countOccurrences_Str_Char_Test_Normal_38 {

    @Test
    public void testCountOccurrencesWithTypicalValues() {
        Assertions.assertEquals(0, TextUtil.countOccurrences("test", 'a'));
        Assertions.assertEquals(0, TextUtil.countOccurrences("", 'a'));
    }

}

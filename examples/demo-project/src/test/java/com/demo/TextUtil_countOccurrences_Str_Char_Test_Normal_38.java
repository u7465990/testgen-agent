package com.demo;

import com.demo.TextUtil;
import org.junit.Test;

public class TextUtil_countOccurrences_Str_Char_Test_Normal_38 {

    @Test
    public void countOccurrences_withTypicalInputs_returnsExpectedCount() {
        org.junit.Assert.assertEquals(0, TextUtil.countOccurrences("", 'a'));
        org.junit.Assert.assertEquals(2, TextUtil.countOccurrences("test", 't'));
        org.junit.Assert.assertEquals(0, TextUtil.countOccurrences("test", 'a'));
    }

}

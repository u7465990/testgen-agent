package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_reverse_Str_Test_Normal_45 {


    @Test
    public void testReverseWithRepresentativeInputs() {
        String result1 = TextUtil.reverse("test");
        Assert.assertEquals("tset", result1);

        String result2 = TextUtil.reverse("");
        Assert.assertEquals("", result2);
    }

}
